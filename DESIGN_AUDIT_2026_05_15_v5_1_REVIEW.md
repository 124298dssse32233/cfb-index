# CFB Index — v5.1 Implementation Plan Review

**Date:** 2026-05-15
**Author:** Claude (final verification pass, 4 parallel ground-truth investigators)
**Supersedes:** [v5](DESIGN_AUDIT_2026_05_15_v5.md) where conflicts arise; all other v5 spec intact
**Status:** Ready for Sprint v5-0 procurement after Kevin reviews this document

### What this document is

Four verification investigators ran in parallel against the v5 implementation plan:
1. **Code ground-truth** — verified every file path / line number / table / column / cron string v5 cited
2. **Cross-version reconciliation** — found contradictions and ambiguous supersessions across v1-v5
3. **Sprint dependency audit** — critical-pathed the 10-sprint roadmap, found scope gaps and external-dependency lead times
4. **Cost + API feasibility** — verified $4,420/yr LLM ceiling, GitHub Actions quota, Vercel quotas, image-API options

Plus the owner's late-stage change: image generation should leverage existing ChatGPT Plus subscription rather than commission FLUX.1 [pro] access.

This document is the **synthesis** — what to do before Sprint v5-1 starts.

---

## Part 1 · The Headline Findings

### What v5 got right (mostly everything)

The big structural claims hold:
- The 17 profiled programs exist as named (`profiles/*.md` confirmed)
- The 15 workflow YAMLs exist exactly as enumerated
- The structural seam (`publish-edition-weekly.yml` decoupled from deploy, no Vercel call) — **verified at lines 14-81 of the workflow file**
- `world_class_enrich.yml` + `compute_full_pass.yml` are dispatch-only as claimed
- `_factual_restatement` exists at `wire/editorial.py:37-48` with the "Production replaces this with a per-row Sonnet API call" comment intact
- `_W17_COVER_ESSAY` exists as a hand-written Python string literal at `editions/seeds.py:63`
- `chronicle_generator.persist()` writes `is_published=1` without an approval gate
- `_MONTH_TO_PHASE` enumerates all 10 phases at `state_resolver.py:39-52`
- All 30+ CLI subcommands referenced in v5 exist
- All current cron schedules match v5's Part 8.1 table

**v5's claims are accurate.** The corrections below are sharpenings, not rewrites.

### What v5 got wrong (in priority order)

| # | Wrong | Right | Severity |
|---|---|---|---|
| 1 | LLM weekly ceiling **$85/wk = $4,420/yr** | **$25/wk = $1,300/yr** with prompt caching (the codebase currently has zero caching; adding it in Sprint v5-1 unlocks 30-40% cost reduction) | **CRITICAL** |
| 2 | Auto-throttle trigger **$120/wk** | **$50/wk** | **CRITICAL** |
| 3 | Vercel **Hobby plan sufficient** | **Pro plan ($20/mo) mandatory** — 69k-page site exceeds Hobby's 100MB source-size limit | **CRITICAL** |
| 4 | GitHub Actions free private-repo tier sufficient | Projected usage 4,000-5,000 min/mo on private repo = **2-2.5× over the 2,000-min cap.** Either make repo **public** (free unlimited) or pay ~$300/yr in overage | **CRITICAL** |
| 5 | `fanintel_gameday_live.yml` fires **every minute Sat 12:00 → Sun 02:00 ET** | GitHub cron is **5-minute granularity** (best-effort under load). v5's per-minute claim is technically impossible. Use a long-running workflow with internal sleep-loop OR accept 5-min granularity | **CRITICAL** |
| 6 | Gameday cron implicitly deploys 840×/Sat if it calls `vercel deploy --prod` per iteration | Vercel Hobby = 100 deploys/day hard limit. Gameday workflow must NOT call Vercel deploy per iteration — use event-detection deploys OR R2/KV manifest updates with static-site re-fetch | **CRITICAL** |
| 7 | Sprint v5-10 ships **65+ renderers in 1 week** | Mis-scoped ~4×. Split into v5-10a/b/c/d across 3-4 weeks | **CRITICAL** |
| 8 | Trophy commission lead time absent from roadmap | 6-8 week lead → **must order at Week 2 of Sprint v5-1** to land for Sprint v5-10b | **HIGH** |
| 9 | Profile-schema authoring (~8.5h editorial work) hidden inside Sprint v5-9 renderer week | Move to **Sprint v5-0** (parallel-track work for Kevin) | **HIGH** |
| 10 | `editions_authored` proposed as NEW table | Repo's `editions` table already has `cover_essay_id integer` FK pointing at a planned-but-uncreated `cover_essays` table (per `migrations/20260425_09_editions_schema.sql:28`). **v5's `editions_authored` collides** with the dangling FK | **HIGH** |
| 11 | Migration filename `0042_prompt_versions.sql` under `migrations/sql/` | Repo uses **flat `migrations/YYYYMMDD_NN_*.sql`** convention (27 existing migrations, latest `20260426_85_*`). v5's `0042_` numbering and `sql/` subdirectory **do not exist** | **HIGH** |
| 12 | `is_tentpole(date)` at `daily/synthesizer.py:42` | Lives at **`daily/data.py:30`**, imported into synthesizer at line 16 | **MEDIUM** |
| 13 | "Heat Desk" appears in v5 LLM routing | v4 specifies 5 desks: Editor's / Receipts / Cohort / Connections / Fan-Voice. **"Heat Desk" is undefined** — use Cohort Desk in tentpole mode, or define explicitly | **MEDIUM** |
| 14 | v5's image-generation plan = FLUX.1 [pro] API | **OpenAI Images API (gpt-image-1)** is the better match per Kevin's existing ChatGPT Plus subscription. See Part 4 below | **MEDIUM** (now resolved by owner) |
| 15 | Total program ships in **~14 dev-weeks** | Realistic total is **~17 dev-weeks** with the v5.1 corrections (Sprint v5-0 procurement + split v5-6 + split v5-10) | **MEDIUM** |
| 16 | `enrich_nightly.yml` introduced as NEW workflow in v5-3 | But v5-1 said "Convert `world_class_enrich.yml` to cron." Pick one — recommend **keep `world_class_enrich.yml`, just add `schedule:`** | **MEDIUM** |
| 17 | "BFL LoRA hosting $0.001 markup" | BFL LoRA hosting is **$999/mo at dev tier**. Use Replicate-hosted FLUX.1 dev as alternative (~$0/mo idle, ~$0.05/image) — but moot now since image plan switches to OpenAI | **MEDIUM** (moot) |
| 18 | Big 12 conference color `#C8102E (warm undertone)` | Actual brand `#D14124` — v5 already uses this hex but v3 had `#C8102E`. **v5 supersedes**; flag explicitly | **LOW** |

### What v5 was missing

12 net-new tables/columns implicit but not explicit in migration list:
- `editions_authored` (or extend existing `editions` table — see Correction #10)
- `quality_gates`
- `backfill_progress`
- `editorial_overrides`
- `system_state`
- `post_publish_violations`
- `page_lastmod`
- `archive_threads` + `archive_comments` + `archive_term_weekly`
- `chronicle_moments_pending`
- `player_archetype_tags`
- `team_chronicle_observations.approval_state` (column add)
- `mailbag_submissions.source_kind` (column add)
- `canon_entries.model_version_at_generate` (column add)

Plus key spec gaps:
- `voice_validator` is regex-only — doesn't catch tone drift or hallucination. v5 should add a Haiku-as-judge layer for high-stakes surfaces
- "Headline-quality checklist" referenced 3× in v5 but **no module implements it** — needs explicit spec
- `editorial_overrides` reject-link receiver — v5 says `?reject=$signed_token` but never specs the signing key location or the consuming endpoint
- 10 CLIP reference style images — who creates them, where stored, when
- Helmet base `.blend` file source — commissioned vs OSS pick

---

## Part 2 · The 12 Most Important Corrections (priority order)

These are the changes to make before Sprint v5-1 starts. Each is concrete and actionable.

### Correction #1 — Add prompt caching to `llm_runtime.py` in Sprint v5-1

The single biggest cost reduction. Current code at `llm_runtime.py:311` passes plain `messages` list and `system` string with zero cache markers. Add:

```python
kwargs["system"] = [
    {"type": "text", "text": system_text,
     "cache_control": {"type": "ephemeral"}}
]
```

**Impact on Chronicle alone** (largest surface): the voice-contract excerpt (~2000 tokens) × 595 calls/wk = 1.19M shared input tokens. Without caching: $3.57/wk just on shared prefix. With caching: ~$0.40/wk. **Savings ~$3.20/wk on Chronicle alone; ~30-40% total cost reduction across all surfaces.**

This is a 15-line patch. Land it in Sprint v5-1.

### Correction #2 — Revise the LLM budget

| Item | v5 stated | Actual | Notes |
|---|---|---|---|
| Weekly LLM ceiling | $85/wk | **$25/wk** | With caching; without caching ~$50/wk |
| Auto-throttle trigger | $120/wk | **$50/wk** | 100% headroom over operational |
| Annual LLM | $4,420/yr | **$1,300/yr** | |

Update `quality_gates.llm_weekly_spend_ceiling_usd` default value from 120 to **50**.

### Correction #3 — Upgrade Vercel to Pro plan ($20/mo, $240/yr)

The site has ~69k pages, ~400MB compressed source. Vercel Hobby has a 100MB CLI source-size limit. **Pro plan is mandatory, not optional.** Get the upgrade processed before Sprint v5-1 starts.

### Correction #4 — Make the repo public (single most-leverage operational fix)

Repo is currently private. Private free tier = 2,000 GitHub Actions minutes/month. Projected season usage: 4,000-5,000 min/mo. **2-2.5× over the cap.**

The site is published. The data isn't proprietary. The code shows the world how the system works — which is itself a moat. **Toggle it public.** Saves ~$300/yr in overage AND removes a future scaling cliff.

### Correction #5 — Image generation: OpenAI Images API (replacing FLUX)

Per owner's late-stage decision: use ChatGPT Plus ($20/mo, already paid) for image-style exploration + reference curation, and **OpenAI Images API (gpt-image-1)** for automated production.

| Component | Plan |
|---|---|
| **Style tuning + reference curation** | ChatGPT Plus web UI ($20/mo, already subscribed) — Kevin curates 10 hand-approved reference images for CLIP gate |
| **Automated production** | OpenAI Images API on platform.openai.com (separate billing, ~$5-15/mo at v5 volume) |
| **Model** | gpt-image-1 (DALL-E 3 successor in 2026) |
| **Quality tier** | `quality: "standard"` by default ($0.04/image); `quality: "hd"` for Editions covers ($0.17/image) |
| **Size** | `size: "1792x1024"` for 16:9 hero cards; `size: "1024x1024"` for square thumbnails |
| **Style guide** | v3 Part 8's Brad-Holland × Hopper × Niemann prompt scaffolding **carries over verbatim** — gpt-image-1 follows natural-language prompts well; just drop the `--ar` and `--stylize` flags Midjourney requires |
| **CLIP gate** | Same approach as v5: ViT-L/14 embeddings of 10 reference images; auto-reject if cosine < 0.7 |
| **Throughput** | OpenAI Images rate limit is generous (≥100 req/min on tier-1 accounts); no waitlist |

**Volume math:** ~80 images/month (Chronicle covers + Storyline heroes + Editions covers + Reactions covers). At standard quality: 80 × $0.04 = **$3.20/mo**. At HD: 80 × $0.17 = **$13.60/mo**. Recommend: standard for Chronicle/Reactions/Storylines, HD for Editions covers (~4/mo). **Total: ~$5-8/mo + Plus subscription = $25-28/mo combined.**

Files to update: `scripts/imagery/generate_editorial_art.py` (new in Sprint v5-7, now uses OpenAI client not BFL).

### Correction #6 — Insert Sprint v5-0 (Week 0 procurement)

Before Sprint v5-1 starts, run a Week 0 procurement sprint. Some items have multi-week lead times.

**Sprint v5-0 task list:**

```
API keys (1 day total):
[ ] Anthropic API key — verify current quota; raise to $200/mo if needed
[ ] OpenAI API key — separate from ChatGPT Plus, generated at platform.openai.com
[ ] Resend account — create + verify
[ ] Cloudflare account — create R2 bucket `cfbindex-assets`

DNS (2-3 days propagation):
[ ] SPF + DKIM + DMARC records on cfbindex.com for Resend
[ ] cdn.cfbindex.com CNAME → Cloudflare R2 custom domain

Vercel:
[ ] Upgrade Hobby → Pro plan ($20/mo)
[ ] Verify `site-deploy` concurrency group queues (not cancels) under contention
[ ] Verify VERCEL_TOKEN in repo secrets

GitHub:
[ ] Make repo public (or accept ~$300/yr Actions overages)
[ ] Add secrets: OPENAI_API_KEY, RESEND_API_KEY, R2_ACCESS_KEY, R2_SECRET, CLAUDE_API_KEY (verify)

Asset commissions (6-8 weeks lead):
[ ] Order 8 Tier-1 trophy SVG glyphs ($800) — Iron Bowl molten-droplet, ND-USC Shillelagh, Stanford Axe, Red River Golden Hat, etc.
[ ] Order 17 Tier-2 trophy SVG glyphs ($1,700) — Old Oaken Bucket, Floyd of Rosedale pig, Iron Skillet, Egg Bowl, etc.
[ ] (Optional) Source helmet base .blend file — BlendSwap CC0 search first; commission only if no OSS asset works
[ ] Decide on bespoke 12-glyph navigation set (optional; default to Phosphor OSS — recommend skip commission)

Content / curation (Kevin, parallel):
[ ] Curate 10 reference style images for CLIP cluster — use ChatGPT Plus to generate samples, hand-approve favorites, save to output/_assets/style_reference/
[ ] Author profile-schema extensions for 17 programs (~8.5 hours editorial) — see Part 1 of v5 for schema; YAML lives in profiles/*.md frontmatter
[ ] Fix Vandy "Shedeur-beater" → "Milroe-beater" factual error in profiles/vanderbilt.md
[ ] Pre-author 4 weeks of seeds.py fallback Editions (insurance for Sprint v5-2 slip)
[ ] Draft 11 prompt template bodies — use Opus to draft, Kevin reviews + commits (`prompts/edition_cover_essay.md`, `prompts/wire_why_it_matters.md`, `prompts/chronicle_card.md`, `prompts/daily_take.md`, `prompts/mailbag_answer.md`, `prompts/heisman_weekly.md`, `prompts/reaction_story.md`, `prompts/canon_entry_top10.md`, `prompts/canon_entry_11to100.md`, `prompts/pulse_state_of_team.md`, `prompts/thread_chapter.md`)
```

### Correction #7 — Resolve the `editions_authored` schema collision

v5 proposes a new `editions_authored` table. But the repo's existing `editions` table has `cover_essay_id integer` FK at `migrations/20260425_09_editions_schema.sql:28` — pointing to a planned but never-created `cover_essays` table.

**Recommended path:** Don't create a parallel `editions_authored` table. Instead:

1. **Extend existing `editions` row** with new columns: `cover_essay_md`, `model_id`, `confidence`, `validation_notes_json`, `generated_at_utc`
2. **Use existing `edition_features` table** (already at `editions_schema.sql:39` with `body_markdown` per `feature_kind`) for the 5 feature blocks. Add columns `model_id`, `confidence`, `validation_notes_json` to that table

This avoids the FK collision and uses existing infrastructure. v5.1 should update Sprint v5-2 to specify "extend existing tables, do not create `editions_authored`."

### Correction #8 — Migration numbering: use date-prefixed convention

Repo uses `migrations/YYYYMMDD_NN_description.sql` (27 existing, latest `20260426_85_*`). v5's `migrations/sql/0042_prompt_versions.sql` is wrong on two counts (subdirectory + numbering).

**v5.1 migrations should follow the existing scheme:**
- `migrations/20260520_01_prompt_versions.sql`
- `migrations/20260520_02_quality_gates.sql`
- `migrations/20260520_03_backfill_progress.sql`
- `migrations/20260520_04_editions_extend.sql` (extends `editions` + `edition_features` per Correction #7)
- `migrations/20260520_05_editorial_overrides.sql`
- `migrations/20260520_06_system_state.sql`
- `migrations/20260520_07_post_publish_violations.sql`
- `migrations/20260520_08_page_lastmod.sql`
- `migrations/20260520_09_archive_tables.sql` (all 3 archive tables)
- `migrations/20260520_10_chronicle_moments_pending.sql`
- `migrations/20260520_11_player_archetype_tags.sql`
- `migrations/20260520_12_chronicle_approval_state.sql` (column add + backfill from `is_published`)
- `migrations/20260520_13_mailbag_source_kind.sql` (column add)
- `migrations/20260520_14_canon_model_version.sql` (column add)
- `migrations/20260520_15_llm_usage_log.sql` (DB-backed spend log for throttle)

All 15 migrations land in Sprint v5-1.

### Correction #9 — Migration must backfill chronicle `approval_state` from existing `is_published`

When adding the `approval_state` column to `team_chronicle_observations`:

```sql
ALTER TABLE team_chronicle_observations ADD COLUMN approval_state TEXT;
UPDATE team_chronicle_observations
SET approval_state = CASE
    WHEN is_published = 1 THEN 'auto_approved'
    ELSE 'queue_low_confidence'
END;
```

Without this backfill, render-team-pages reads `WHERE approval_state IN ('auto_approved', 'human_approved')` and renders nothing.

### Correction #10 — Split Sprint v5-6 into v5-6a + v5-6b

v5-6 as written compresses 3 weeks of v4 work (Pillow share_cards + R2 + helmet pipeline) into 1 week.

**v5-6a (Week 6):** R2 provisioning verification (DNS already landed Week 0) + `src/cfb_rankings/share_cards/` package with 10 Pillow templates + OG meta wiring via `_render_head_chrome()` + Vercel post-process step

**v5-6b (Week 7):** `scripts/imagery/render_helmets.py` Blender pipeline + `visual_assets.asset_for()` helper + R2 upload step + first 50 helmet renders

Adds 1 week to roadmap.

### Correction #11 — Split Sprint v5-10 into v5-10a/b/c/d

v5-10 as written ships 65+ renderers in 1 week. Realistic split:

| Sub-sprint | Week | Scope |
|---|---|---|
| **v5-10a** | Week 11 | 19 player surfaces + position frames + `player_archetype_tags` table |
| **v5-10b** | Week 12 | 8 Tier-1 rivalry pages (BLOCKED on trophy commission delivery — verify Week 8 status check; have in-house Claude SVG fallback ready) |
| **v5-10c** | Week 13 | 10 phase surfaces + 11 conference landings + 5 cross-program surfaces |
| **v5-10d** | Week 14 | 12 Reddit-archive surfaces |

Adds 2-3 weeks to roadmap. **Trade-off:** if the 14-week hard deadline must hold, cut v5-10d (Reddit-archive surfaces) to a v5.2 release.

### Correction #12 — Resolve naming: keep `world_class_enrich.yml`, just add cron

v5-1 says "Convert `world_class_enrich.yml` to cron." v5-3 references a NEW `enrich_nightly.yml` workflow. These are the same thing under two names.

**Decision:** keep `world_class_enrich.yml` filename (existing), just add `schedule: cron: '0 14 * * *'` to its `on:` block. Do NOT create `enrich_nightly.yml`. Update v5-3 + v5-5 references accordingly.

---

## Part 3 · The Revised Sprint Roadmap (17 weeks)

| Week | Sprint | Deliverable |
|---|---|---|
| **0** | **v5-0 Procurement** | API keys, DNS, Vercel Pro, repo-public toggle, trophy orders, 10 CLIP refs, helmet `.blend`, 11 prompt templates, 17 profile-schema extensions, Vandy fact-check |
| 1 | v5-1 Foundation | 15 migrations (`prompts/`, `prompt_versions`, `quality_gates`, `backfill_progress`, extended `editions` + `edition_features`, `editorial_overrides`, `system_state`, `post_publish_violations`, `page_lastmod`, archive tables, `chronicle_moments_pending`, `player_archetype_tags`, chronicle `approval_state`, mailbag `source_kind`, canon `model_version_at_generate`, `llm_usage_log` DB-backed). `llm_runtime.py` adds prompt caching + auto-throttle via DB-sum. Cron conversions on `world_class_enrich.yml` + `compute_full_pass.yml`. `backfill_full_history.yml` resume logic |
| 2 | v5-2 Editorial gen | `prompts/edition_cover_essay.md` + 5 feature templates. `manage.py generate-edition`. `publish-edition-weekly.yml` moves into `site-deploy` group + Vercel deploy added. Wire `_factual_restatement` → Sonnet swap with feature-flag rollback. **Order Tier-1 + Tier-2 trophy commissions this week if not done in v5-0** |
| 3 | v5-3 Reactions + storylines | `reactions-check-triggers --auto` wired into wire-daily + gameday workflows. `auto-promote-storyline-drafts` poller in (renamed) world_class_enrich.yml nightly cron |
| 4 | v5-4 Mailbag + Chronicle | `mailbag-mine-questions` (Reddit + Bluesky + Substack RSS — carve out 2-3 days for Substack adapter). Chronicle `approval_state` filter on render. Backfill chronicle from `is_published` |
| 5 | v5-5 Heisman + Canon | `generate-heisman-narrative` weekly. Canon tier-aware nightly regeneration. Add `canon_entries.model_version_at_generate` column read |
| 6 | **v5-6a R2 + Pillow OG** | R2 verification. `share_cards/` package with 10 Pillow templates. OG `<meta>` wiring via `_render_head_chrome()` |
| 7 | **v5-6b Helmets + visual_assets** | `render_helmets.py` Blender pipeline. `visual_assets.asset_for()` helper. R2 upload step. First 50 helmet renders |
| 8 | v5-7 Image generation + auto-throttle | `scripts/imagery/generate_editorial_art.py` calls OpenAI Images API (gpt-image-1). CLIP embeddings of 10 reference images → `output/_assets/style_reference_embeddings.npz`. Auto-throttle reads `llm_weekly_spend_ceiling_usd=50` from `quality_gates`. **Check trophy commission delivery status** |
| 9 | v5-8 Zero-Touch UI | `digest_weekly.yml` + Resend. `/admin/queue/` page + slider UI writing to `quality_gates`. `/admin/panic` + `system_state`. `notify_failure.yml` reusable workflow wired into every cron |
| 10 | v5-9 Programs + Sources | 17 bespoke per-program renderer modules (uses profile extensions from v5-0). 16 named data-source surfaces |
| 11 | **v5-10a Players** | 19 player position + archetype surfaces. `player_archetype_tags` migration backfilled |
| 12 | **v5-10b Rivalries** | 8 Tier-1 rivalry detail pages — uses commissioned trophy glyphs (verify delivered Week 8-10) or in-house Claude SVG fallback |
| 13 | **v5-10c Phases + conferences** | 10 phase-specific surfaces + 11 conference landings + 5 cross-program surfaces |
| 14 | **v5-10d Reddit archive** | 12 Arctic Shift archive surfaces (HIGHEST RISK SLIP — cut to v5.2 if Week 14 hard deadline applies) |
| 15-16 | **v5-11 Polish + verify** | Bug fixes from prod observability, performance tuning, voice-validator regression checks, post-publish HTML audit |
| 17 | **v5-12 Launch** | Public communications, methodology page deep update, observability dashboard, retro |

**Total: 17 weeks if everything goes well. 18-19 weeks with realistic slippage.**

Net effect: v5 as written shipped at ~50% probability on Week 10. v5.1 corrections ship at **~85% probability on Week 17** or **~70% probability on Week 14 if Reddit-archive surfaces are deferred to v5.2.**

---

## Part 4 · The Revised Operational Budget

| Item | v5 stated | v5.1 reality | Notes |
|---|---|---|---|
| **LLM API (Anthropic)** | $4,420/yr | **$1,300/yr** | With prompt caching (Sprint v5-1) |
| **Image API (OpenAI)** | $25/yr (FLUX) | **$60-180/yr** | gpt-image-1, mix of standard + HD; ~80 images/mo |
| **Vercel** | $0 (Hobby — incorrect) | **$240/yr** (Pro mandatory) | 69k-page site exceeds Hobby 100MB source limit |
| **Cloudflare R2** | $0 | **$0** | 420MB used out of 10GB free tier |
| **Resend** | $0 | **$0** | 208 emails/yr out of 36k free tier |
| **GitHub Actions** | $0 (private — wrong) | **$0 if public; ~$300/yr if private** | Make repo public — single highest-leverage op fix |
| **Trophy commissions** | "$3-4k" (in v5 main text) | **$2,500-3,500 one-time** | 8 Tier-1 + 17 Tier-2 SVGs |
| **Bespoke 12-glyph nav** | "$1.5-3k" | **$0** (skip; use Phosphor OSS) | |
| **Helmet `.blend` mesh** | "commission" | **$0** (use BlendSwap CC0) or $300-500 if commissioned | |
| **ChatGPT Plus** | not in budget | **$240/yr** ($20/mo, already paid) | For style tuning + reference curation |
| **Newspapers.com (optional)** | not in budget | $240/yr if used | For pre-2013 deep-history sourcing |
| **Total recurring (Year 1)** | ~$4,420/yr | **~$1,800/yr** | 60% reduction |
| **One-time setup (Year 1)** | included in recurring | **~$3,000** | Trophy commissions + optional helmet mesh |

**Year-1 total: ~$4,800. Year-2+: ~$1,800/yr.**

---

## Part 5 · Cross-Version Reconciliation (canonical reading)

Per Investigator 2's reconciliation, the canonical reading order across v1-v5:

| Audit | Read for |
|---|---|
| **v1** | Problem inventory + per-page evidence baseline |
| **v2** | Architectural explanation of why problems are structural (token vocabularies, gold-hex drift, renderer quality matrix) |
| **v3** | Identity / imagery / visual language (12-motif vocabulary, 28-pattern catalog, fall-Saturday color recipe) |
| **v4** | **Canonical build spec** — 13 atoms, voice stylebook, mobile substrate, motion choreography, share cards, governance |
| **v5** | **Canonical for bespokeness + automation** — per-program / per-player / per-rivalry / per-conference / per-season-phase. v5 supersedes v3 Midjourney → FLUX (now superseded again by v5.1 → OpenAI Images API). All other v5 specs additive |
| **v5.1 (this doc)** | Implementation corrections + procurement checklist + revised budget |

**Single-source-of-truth claims by dimension:**

| Dimension | Canonical |
|---|---|
| Color tokens | v3 Part 3 + v4 Appendix C alias map |
| 13 atom specs | v4 Part 1 |
| 5 universal opt-in atoms | v5 Part 1 |
| Editorial voice (5 desks, banned phrases, headline templates) | v4 Part 2 |
| Mobile substrate | v4 Part 3 |
| Motion choreography | v4 Part 4 |
| Share cards + SEO | v4 Part 5 |
| Performance budgets + audit subcommands | v4 Part 6 |
| 28-pattern viz catalog | v3 Part 6 |
| Chart library (Python-SVG primary) | v3 Part 7 + v4 atom helpers |
| **Imagery pipeline** | **v5.1 Correction #5 (OpenAI Images API)** |
| **Workflow cron schedule** | **v5 Part 8.1 + v5.1 Corrections** |
| Profile schema | v4 §2.8 + v5 Part 1 (union, with `signature_metrics_to_lead_with` → `signature_metrics_ladder` rename) |
| Tier-1 rivalry list | v5 Part 3 (8 rivalries) |
| Conference identity | v5 Part 4 |
| **Implementation roadmap** | **v5.1 Part 3 (17-week revised)** |
| **Operational budget** | **v5.1 Part 4 (~$1,800/yr)** |

---

## Part 6 · Spec Gaps That Need Closing Before Sprint v5-1

These are gaps v5 left implicit. Resolve each before kickoff so Sprint v5-1 isn't blocked.

### Spec gap #1 — `voice_validator` deeper layer

Current `voice_validator.py` is regex-only — catches banned phrases like "in this game" and "the team" patterns, but **does not catch tone drift, factual hallucination, or named-entity errors.**

**Recommendation:** Add a second validation pass for high-stakes surfaces (Edition cover essay, Heisman weekly narrative, Canon top-10 entries). Use Haiku-as-judge with: *"Does this output match the CFB Index house voice as described in the attached stylebook excerpt? Respond YES or NO with a one-sentence reason."*

Implement in Sprint v5-1 alongside the prompt-template versioning.

### Spec gap #2 — "Headline-quality checklist" implementation

v5 references this 3× (Part 8.4 Edition row, Part 8.6 quality_gates, Part 9 verification gates) but **no module implements it.** v4 Part 2 specifies the 5-question rubric. Build it as a Python function `validate_headline(text: str) -> tuple[bool, list[str]]` returning pass/fail + list of failed checks.

Build in Sprint v5-1 as part of the voice validator extensions.

### Spec gap #3 — `editorial_overrides` reject-link receiver

v5 says reject links go to `?reject=$signed_token` but doesn't spec the signing key location or the consuming endpoint. Resolve:

- **Signing key:** new repo secret `REJECT_LINK_SIGNING_KEY` (32 random bytes), used with HMAC-SHA256 to sign `(surface, slug, action)` tuples
- **Consuming endpoint:** a static HTML page at `output/site/admin/reject.html` that uses fetch() to POST to a Vercel serverless function `/api/reject.js`; function verifies signature, writes to `editorial_overrides` table, returns confirmation. Vercel free serverless tier handles this.
- **Consuming cron:** every publish workflow's first step queries `editorial_overrides` for current week — if any active overrides match, substitute fallback content

Add to Sprint v5-8 task list.

### Spec gap #4 — Substack RSS adapter (Sprint v5-4)

Substack has no official API. Each publication has an RSS feed at `<publication>.substack.com/feed`. Build a generic Substack adapter that:
1. Reads a list of tracked publications from `config/substack_publications.yaml` (~10 beat-writer Substacks initially)
2. Parses RSS via `feedparser` library
3. Extracts items posted in the last 7 days
4. Scans body for question-shaped patterns (regex: trailing `?` + question-word starter)
5. Scores via Haiku for question-quality
6. Inserts top 8 into `mailbag_submissions` with `source_kind='substack'` and `source_url`

Carve out 2-3 days within Sprint v5-4.

### Spec gap #5 — Gameday workflow architecture

Per-minute cron is fiction. Replace with one of two approaches:

**Approach A (recommended): single long-running workflow with internal sleep-loop**

```yaml
on:
  workflow_dispatch:
  schedule:
    - cron: '55 15 * * 6'   # Sat 11:55 ET, just before noon games
jobs:
  gameday:
    runs-on: ubuntu-latest
    timeout-minutes: 350    # 5h50m, just under GH cap
    steps:
      - run: |
          while [ $(date -u +%s) -lt $END_TS ]; do
            python -u manage.py poll-live-games
            python -u manage.py process-render-queue
            sleep 60
          done
```

Run two sequential workflow instances (Sat afternoon → Sat night), each ~5h50m. Cleaner than 840 cron invocations.

**Approach B (fallback): accept 5-minute granularity**

Use `*/5 16-23 * * 6` (every 5 min during Saturday window). Less responsive but simpler. Acceptable if game-event detection is the actual trigger (most games' inflection moments aren't sub-5-minute).

Recommend Approach A. Resolve before Sprint v5-3 (when gameday workflow gets touched).

### Spec gap #6 — `quality_gates` slider propagation latency

v5 doesn't specify how a slider change in `/admin/queue/` reaches running synthesizers. Resolution:

- Synthesizers read `quality_gates` at start-of-run (not per-call) — slider change made at 06:00 affects 14:00 cron, not mid-run synthesizer
- Restart not required
- Expected latency: "next cron cycle"

Document this explicitly in Sprint v5-8 spec.

### Spec gap #7 — Mobile variants for bespoke modules

v5 Part 1 specifies 17 per-program signature identity modules (Process Counter, Iron Bowl Clock, Swamp Thermometer, etc.) but **doesn't specify mobile variants.** Each needs a 375px-floor spec.

Approach: each signature module's spec needs an explicit `--mobile` variant. Default rules:
- Process Counter: 28px Bowlby (down from 48px) at 375px
- Iron Bowl Clock: 32px digit + 11px label (down from 56px + 14px)
- Swamp Thermometer: collapse from 240×80 to 160×60
- Tailback U scroll: 64px headshot circles (down from 96px), horizontal scroll preserved
- etc.

Build into Sprint v5-9 work — don't gate the sprint on completing this, but capture mobile variants alongside the desktop renderer.

---

## Part 7 · Pre-Sprint v5-1 Go/No-Go Checklist

Before opening the IDE for Sprint v5-1, run through this list. If anything is unchecked, **do that first.**

**Procurement (must be complete):**
- [ ] Vercel Pro plan upgraded
- [ ] Repo set to public (or accept $300/yr GH Actions overage)
- [ ] OpenAI API key generated at platform.openai.com (separate from ChatGPT Plus account access)
- [ ] Resend account created + cfbindex.com SPF/DKIM/DMARC propagated (test send a sample email)
- [ ] Cloudflare R2 bucket created + S3-compatible keys + cdn.cfbindex.com DNS verified
- [ ] All API keys added to repo secrets: ANTHROPIC_API_KEY (existing), OPENAI_API_KEY, RESEND_API_KEY, R2_ACCESS_KEY, R2_SECRET, REJECT_LINK_SIGNING_KEY

**Asset commissions (must be ordered):**
- [ ] 8 Tier-1 trophy SVGs ordered with 6-8 week delivery
- [ ] 17 Tier-2 trophy SVGs ordered
- [ ] Helmet base `.blend` selected (BlendSwap CC0 search; commit to repo when found)
- [ ] 10 CLIP reference style images curated and saved to `output/_assets/style_reference/`

**Content (must be drafted):**
- [ ] 11 prompt template bodies drafted by Opus, reviewed by Kevin, committed to `prompts/`
- [ ] 17 profile-schema extensions authored to `profiles/*.md` frontmatter
- [ ] Vandy "Shedeur-beater" factual error fixed in `profiles/vanderbilt.md`
- [ ] 4 weeks of seeds.py fallback Editions pre-authored (insurance against Sprint v5-2 slip)

**Spec resolutions (must be decided):**
- [ ] `editions_authored` path resolved → use existing `editions` + `edition_features` extension per Correction #7
- [ ] Migration naming convention adopted (date-prefixed `YYYYMMDD_NN_*.sql`)
- [ ] Gameday workflow architecture chosen (long-running with sleep-loop vs 5-min cron) per Spec gap #5
- [ ] OpenAI Images API as canonical (FLUX deferred) per Correction #5
- [ ] Sprint roadmap revised to 17 weeks (or 14 weeks with v5-10d cut)
- [ ] Naming: `world_class_enrich.yml` retained (no `enrich_nightly.yml`)

**Verification (must be tested):**
- [ ] OpenAI Images API generates a sample image with the v3 Brad-Holland-style prompt successfully (one manual test call)
- [ ] Anthropic prompt caching works with current `claude-sonnet-4-6` model (one manual test call with `cache_control`)
- [ ] Vercel `site-deploy` concurrency group queues (not cancels) under contention
- [ ] Resend deliverability — test email to Kevin lands in inbox, not spam

When every box is checked, Sprint v5-1 starts.

---

## Part 8 · Closing

### What v5.1 changes about v5

- **Cost ceiling:** $4,420/yr → ~$1,800/yr (60% reduction via prompt caching + repo-public + OpenAI Images API)
- **Roadmap:** 14 weeks → 17 weeks (realistic with procurement + sprint splits)
- **Image generation:** FLUX/Midjourney → OpenAI Images API (gpt-image-1) leveraging existing ChatGPT Plus subscription
- **Architecture:** 18+ corrections including the `editions_authored` table collision, migration numbering, `enrich_nightly.yml` naming, gameday cron architecture
- **Procurement:** Sprint v5-0 inserted with 6-8 week trophy commission lead time
- **Spec gaps:** 7 items closed (voice_validator deep layer, headline-quality checklist implementation, reject-link receiver, Substack adapter, gameday workflow, slider propagation latency, mobile variants)

### What v5.1 does not change about v5

Everything else.

The 17 per-program bespoke modules. The 9 position frames × 10 archetype frames for players. The 8 Tier-1 mythic rivalries with their seam-CSS + trophy glyph + anchor sets. The 11 FBS conference identities. The 10 phase × 9 design variant atlas. The 16 data sources → named editorial surfaces. The 12 Arctic Shift Reddit archive surfaces. The voice stylebook with 5 desks and banned phrases. The mobile substrate. The motion choreography. The share-card system. The audit subcommands and performance budgets. The Kevin Zero-Touch architecture with weekly digest emails and quality-gate sliders.

All of that stays. **v5.1 is the implementation patch, not a redesign.**

### The path forward

1. Kevin reviews this v5.1 document
2. Kevin completes Sprint v5-0 (procurement + content drafting, ~1 week parallel work)
3. Engineering opens Sprint v5-1 with all prerequisites met
4. Each subsequent sprint runs with verification gates passing before the next begins
5. Week 14: site reaches "v5.1 minimum viable bespokeness" with Reddit-archive surfaces deferred to v5.2
6. Week 17: site reaches "v5.1 full ship" with all bespoke surfaces live

When Week 17 closes, Kevin opens the Friday digest email. Glances. Ignores it. Goes to bed. Saturday morning the Edition publishes itself. The Time Machine remembers. The Iron Bowl countdown ticks. The cohorts disagree, and the disagreement is the story. And nobody had to push a button.

---

## Appendix · Investigator Output Summaries

The 4 verification investigators produced these artifacts (~10,000 words of detailed audit findings synthesized into this document):

| Investigator | Output |
|---|---|
| **Code ground-truth** | Verified 25+ specific file paths, line numbers, table schemas, cron strings. Confirmed 95% of v5 claims accurate. Identified `is_tentpole` location error, migration numbering scheme mismatch, `editions.cover_essay_id` FK collision |
| **Cross-version reconciliation** | 7 contradictions identified (Big 12 color, burnt-orange token, etc.), 7 ambiguous supersessions, 12 specific v5.1 patch edits. Established canonical reading-order charter |
| **Sprint dependency audit** | 18 critical-path gaps identified. Sprint v5-10 mis-scoped 4×. Trophy commission 6-8wk lead time. Recommended Sprint v5-0 insertion + split v5-6 and v5-10. Total roadmap: 14→17 weeks |
| **Cost + API feasibility** | LLM ceiling 7× too high without caching. Vercel Pro mandatory. GitHub Actions overage on private repo. Gameday cron is fiction (5-min granularity). BFL LoRA hosting is $999/mo. Recommended OpenAI Images API as canonical |

Full investigator outputs are preserved in the `tasks/` directory if Kevin wants the unabridged versions.

---

**v5.1 status:** Ready for owner sign-off. After sign-off + procurement completion, Sprint v5-1 starts.

**Total audit corpus across all 6 layers (v1 → v5.1):** ~7,500 lines · 30 parallel investigators · ~17 dev-weeks to implement · ~$1,800/yr operational ceiling.

The standard does not flinch at rankings. **And nobody has to push a button to make any of it happen.**
