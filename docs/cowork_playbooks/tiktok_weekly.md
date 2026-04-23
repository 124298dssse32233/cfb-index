# TikTok Creator Observation Playbook

**Cadence**: weekly, Friday afternoon (STRATEGY §7, Tier 2 manual).
**Time budget**: 20 minutes.
**Source**: `tiktok_observed` — Tier C, rank/trend publication only.

TikTok is the highest-signal source for Gen Z and college-age cohorts (STRATEGY §4 weights: `gen_z=0.65, college_age=0.35`) but we don't run a programmatic pipeline — the platform fights automation aggressively and ToS is clear. Instead, Claude observes 30 curated creator profiles via Cowork-Chrome and writes a weekly rank snapshot.

---

## Creator roster (30 curated)

Maintained in `seeds/tiktok_creators.yaml` (created in TASK 6.2 follow-up). Curation principles:

- **15 national CFB creators** — broad reach, no single-team alignment (Urban Meyer's son-in-law type).
- **10 team-aligned student-creator accounts** — one per priority_teams row where an active account exists.
- **5 HBCU creators** — coverage gap callout in STRATEGY §9.

Accounts are dropped from the roster if they go private, inactive (<1 post/30d), or pivot off CFB. The roster refreshes monthly in the Deep Research pass (STRATEGY §7).

---

## Observation schema

For each creator, per week, record ONE row:

```yaml
source_id:          tiktok_observed
source_tier:        C
platform:           tiktok
creator_handle:     "@handle"                  # no real names
author_identity_class: pseudonymous
observed_at_utc:    ISO-8601
followers:          integer
following:          integer
likes_total:        integer                    # lifetime account likes
top_video_url:      URL of #1 video in last 7 days
top_video_views_7d: integer
top_video_comments_7d: integer
top_video_caption:  first 200 chars
demographic_slice:  gen_z_creator
geographic_origin:  self-declared if bio lists a city/school, else null
capture_url:        creator's profile URL
canonical_url:      same
retention_policy:   aggregated_only
ingestion_adapter_version: 0.1.0-manual
dedup_key:          sha1("{creator_handle}|{observed_week}")
notes:              optional 1-line qualitative observation
```

The 30 rows per week become rank inputs — we publish "creator X rose from #12 to #4 in follower-growth-rate" but never a raw follower number as a fan-intelligence signal. That's the Tier C rule.

---

## Navigation steps

1. Open Cowork-Chrome on `https://www.tiktok.com/@{handle}` for each creator.
2. TikTok shows follower/following/likes in the header; copy those.
3. Click "Videos" tab; scroll to identify the **most-viewed video in the past 7 days**.
4. For that video: copy URL, view count, comment count, and the first ~200 chars of the caption.
5. If the creator's bio says "LSU '25" or similar, capture that in `geographic_origin` as self-declared.
6. If the creator pinned a video sponsored by a gambling sponsor or has "#ad" in the top-7d video, flag in `notes` — we may demote that row's influence downstream.

---

## What NOT to capture

- **Comments on videos** — too much noise, too much duplication with Reddit/BlueSky.
- **Creator DMs** — obviously.
- **Account demographics** — TikTok doesn't expose verified age/location; do not infer from appearance.
- **Student athletes' personal accounts** — even if popular. They're the subject of fan sentiment, not the sample.
- **Minors** — if a creator self-identifies as under 18, or their bio says "HS '26" (high school), skip.

---

## Row writing

At session end:

```
python manage.py cowork-ingest-tiktok --week=YYYY-WW --yaml=<paste>
```

The CLI (TASK 6.2 follow-up) validates the schema, assigns `dedup_key`, and inserts into `conversation_documents` with `source_id=tiktok_observed`, `source_tier=C`. Duplicate (same `dedup_key`) → silent skip.

---

## Weekly rank computation

After the raw rows land, a follow-up `python manage.py compute-tiktok-ranks --week=YYYY-WW` produces:

- Per-creator follower-growth rank (delta vs. prior week).
- Per-creator 7d-view rank.
- Which team's creator pool showed the biggest week-over-week activity shift.

These ranks feed the `gen_z` cohort effective-N. No raw numbers leak to publication.

---

## Drift + escalation

- **Creator goes private**: mark inactive in roster, do NOT attempt workaround.
- **Creator deletes a flagged top-video before we publish**: drop the row entirely. Don't preserve a caption-with-no-citation.
- **TikTok adds stricter bot detection and Cowork can't load the page**: escalate to Kevin; do not use automation tools as workaround.
- **A creator is outed as using stolen content / fake followers**: purge all their rows and add to a `creators_blocked` list; note reason.
