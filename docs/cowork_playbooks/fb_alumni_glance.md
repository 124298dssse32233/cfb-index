# Facebook Alumni Glance Playbook

**Cadence**: Weekly, Saturday morning (STRATEGY §7 Tier 2 / §3 `facebook_alumni_glance`).
**Time budget**: 20 minutes.
**Source**: `facebook_alumni_glance` — Tier D, citation only. Never a number.

Facebook's graph API no longer allows programmatic access to Pages or Groups, and our policy forbids scraping private Groups regardless. What IS allowed: **public, non-logged-in observation of public alumni Pages**, one human glance per week, and storing only pseudonymized pull-quotes with a backlink. This playbook formalizes that.

---

## Target list (10 public Pages)

Maintained in `seeds/facebook_alumni_pages.yaml` (TASK 6.4 follow-up). Selection criteria:

- Page is publicly viewable (no login required).
- Page is an official alumni association OR a large public alumni Page with ≥10k followers.
- Page posts at least monthly about football (if dormant, it's dropped).

One Page per team where one exists. We expect ~10-14 Pages total, weighted toward programs with stronger alumni networks (Alabama, Michigan, Notre Dame, FSU, Howard, HBCU-Gameday national).

---

## Per-Page observation steps

1. Kevin opens `https://www.facebook.com/{page_name}` in an incognito browser window (NOT logged in). Cowork observes.
2. Look at the **3 most recent posts in the past 7 days** that mention football (team, game, coach, recruiting, NIL).
3. For each such post, record ONE row using the schema below.
4. If the Page has posted nothing football-related in 7 days, record a single row with `status=no_football_chatter` — signal is valid.
5. Do NOT scroll into comments. Do NOT click on posters. Glance only.

---

## Row schema

```yaml
source_id:              facebook_alumni_glance
source_tier:            D
platform:               facebook
page_handle:            "AlabamaAlumniAssoc"
page_team_id:           <priority_teams.team_id>
observed_at_utc:        ISO-8601
post_observed_timestamp: ISO-8601 of the post itself
author_identity_class:  official                 # Pages are officially-run
post_excerpt:           first 280 chars, VERBATIM (it's public)
post_engagement_likes:  integer (if shown)
post_engagement_comments: integer (if shown)
capture_url:            direct URL to the post
canonical_url:          same
demographic_slice:      alumni_diaspora
retention_policy:       citation_only
ingestion_adapter_version: 0.1.0-manual
dedup_key:              sha1("{page_handle}|{post_observed_timestamp}")
notes:                  optional 1-line qualitative take (e.g., "rally cry", "concern about coaching")
```

---

## What NOT to capture

- **Individual commenters** — even if the Page is public. Commenters haven't consented to sampling.
- **Personal Pages or Profiles** — only official alumni Pages. If you can't see it without logging in, don't.
- **Private or "Closed" Groups** — absolutely not. Doesn't matter if Kevin is a member.
- **Real names** — even from the Page's admin signature if it exposes one. Author_identity_class is `official` and that's the only identifier that ships.
- **Images / video content** — pass. We're here for text excerpts only.

---

## Row writing

```
python manage.py cowork-ingest-fb-alumni --week=YYYY-WW --yaml=<paste>
```

The CLI (TASK 6.4 follow-up) validates schema, assigns dedup_key, inserts into `conversation_documents` with `source_tier=D`. These rows **never** contribute to numeric aggregates; they appear exclusively as pull-quote citations in editorial narratives.

---

## Escalation

- **Page starts requiring a login mid-session**: stop observing it. FB quietly A/Bs this. If the requirement persists for 2 sessions, drop the Page from the roster and note in SESSION_LOG.
- **A Page's post becomes inaccessible after capture**: we keep the stored excerpt with `canonical_url` now 404 — the citation breaks honestly, we do not substitute an archive.
- **Kevin's personal FB login triggers by accident**: close the tab. Do not resume the session. Meta tracking cookies may have been set.
