# Monday Board Sweep Playbook (v1)

**Cadence**: Every Monday 09:00 ET, 45 minutes in-season (STRATEGY §7).
**Scope**: First 5 boards. Expansion to 20 in TASK 6.1.
**Goal**: ~20 new rows per board per week, written to `conversation_documents` with full provenance.

This playbook is designed for **Cowork-Chrome assist**: Kevin opens each board URL, Claude observes the page via the Cowork extension, and Claude writes structured rows to SQLite via the CLI. If a board blocks bots aggressively, Kevin copy-pastes the thread text into the Cowork chat and Claude parses from there — either way the extraction schema below is the same.

---

## Boards in scope (v1)

| Board | Team | source_id | Fandom tilt |
|---|---|---|---|
| tigerdroppings.com | LSU | `board_tigerdroppings` | local, older, die-hard |
| shaggybevo.com | Texas | `board_shaggy_bevo` | independent, recruiting-savvy |
| volnation.com | Tennessee | `board_volnation` | local, die-hard |
| tidefans.com | Alabama | `board_tidefans` | local, older |
| 11warriors.com | Ohio State | `board_11warriors` | blog+forum hybrid, national-tilt |

Every row these adapters produce writes to `source_registry.source_id` = the `board_*` id above. A one-time seed run instantiates those five from the `board_template` row via:

```
python manage.py seed-source-registry-instance --family=board --team=LSU --board=tigerdroppings
```

(CLI planned for TASK 6.1 — for v1, rows inherit `board_template` weights by convention.)

---

## Extraction schema

Every thread observed produces exactly this row shape. Fields map 1:1 onto `conversation_documents` + its new provenance columns (TASK 1.1).

```yaml
source_id:              board_tigerdroppings           # matches source_registry.source_id
source_tier:            B                              # always B for boards
platform:               message_board
source_document_id:     "thread:{board_domain}:{thread_id}"
source_parent_document_id: null                        # fill if it's a reply
source_author_name:     pseudonym                      # NEVER real name; boards are pseudonymous
author_identity_class:  pseudonymous
title_text:             thread title (verbatim)
body_text:              opening post body (≤4000 chars; truncate mid-sentence if longer)
external_created_at_utc: ISO-8601 thread start time (from page metadata)
collected_at_utc:       now()
like_count:             number if board exposes it, else NULL
reply_count:            total replies on thread
view_count:             if exposed, else NULL
demographic_slice:      hardcore_board
geographic_origin:      null                           # boards don't expose; leave null
capture_url:            full URL of the thread page
canonical_url:          same as capture_url unless the board has a "permalink" link
retention_policy:       aggregated_only                # don't keep raw body >90 days
ingestion_adapter_version: 0.1.0
dedup_key:              sha1("{board_domain}|{thread_id}|{external_created_at_utc}")
raw_retention_policy:   purge_90d
language_code:          en
```

If a thread has >1 pull-quote worth attention, create ONE row per notable post, linking via `source_parent_document_id` to the OP's `source_document_id`. Do NOT scrape entire comment trees — the goal is signal, not archive.

---

## Per-board navigation steps

### tigerdroppings.com (LSU)

1. Go to https://www.tigerdroppings.com/rant/o-t-lounge/list.aspx — the O-T Lounge, which generates the most football-adjacent chatter.
2. Also hit https://www.tigerdroppings.com/rant/lsu-sports/list.aspx — on-topic.
3. For **each thread with >50 replies** posted in the last 7 days, record ONE row using the schema above.
4. Stop at 5 threads per subforum, 10 rows total for this board.
5. If the thread contains a coach-name, QB-name, or rival mention, flag `demographic_slice: hardcore_board` AND add tag `key_storyline` in the Cowork session log (not the DB — the weekly brief will pick these up).

### shaggybevo.com (Texas)

1. Go to https://shaggybevo.com/community/forums/west-mall-20.0/ — the main football board (bounce one folder deeper if their nav has changed).
2. Sort by "Latest reply."
3. Top 10 threads, same per-thread rules as above.
4. Shaggy Bevo has a paid-tier; **stop at any paywall**. Do not click through.

### volnation.com (Tennessee)

1. Go to https://www.volnation.com/forum/ — look for "Primary Site" or "Tennessee Football" subforum.
2. Sort by "Most recent post."
3. Top 10 threads.
4. VolNation occasionally geotags — capture the `geographic_origin: self-declared` if a poster states "From Nashville" in their sig. Leave null otherwise.

### tidefans.com (Alabama)

1. Go to https://www.tidefans.com/forums/ — main football subforum.
2. Sort by latest activity.
3. Top 10 threads.
4. TideFans aggressively rate-limits non-logged-in visitors. Kevin should be logged in before Cowork starts; Claude does NOT store the login cookie.

### 11warriors.com (Ohio State)

1. Go to https://www.elevenwarriors.com/forum — note Eleven Warriors is blog+forum hybrid.
2. The forum sidebar has "Most Recent" — start there.
3. Top 10 threads.
4. Eleven Warriors blog posts themselves are NOT board rows — those are tracked as `substack_template` / Substack-like RSS elsewhere.

---

## What NOT to capture

- **PMs / DMs** — never, even if accidentally visible.
- **Login-walled subforums** — if a subforum requires a paid tier (247Sports premium, Rivals gold), skip. Free tier only.
- **Real names** — even if a poster self-identifies in-thread, store pseudonym only. Set `author_identity_class: pseudonymous`.
- **Minors** — if a poster self-identifies as under 18, skip the row entirely.
- **Personally-identifying info** — phone numbers, addresses, employer names: strip before writing.
- **Raw image uploads / attachments** — don't download. Reference by URL if they're clearly part of the discussion, otherwise ignore.

---

## Row writing (at end of session)

From the Cowork chat, run:

```
python manage.py cowork-ingest-board-sweep --session=monday_YYYYMMDD --yaml=<paste>
```

The CLI (to be built in TASK 5.2+) validates the extraction schema, assigns `dedup_key` if missing, and inserts into `conversation_documents`. Rows already present (same `dedup_key`) are silently skipped.

After insert, Claude prints:

```
tigerdroppings:  9 new, 1 dedup
shaggybevo:     10 new, 0 dedup
volnation:      8 new, 2 dedup
tidefans:       10 new, 0 dedup
11warriors:     7 new, 3 dedup
total:          44 new, 6 dedup — weekly target met ✓
```

If ANY board returns 0 new rows, write a row to `scrape_health` with `status=empty` and note in the Monday brief — likely board is down, paywalled, or boycotted.

---

## Drift checks (monthly)

Once per month (first Monday), Claude runs:

```
python manage.py audit-board-drift --weeks=4
```

which looks for:
- Boards with declining row counts (possible layout change).
- Boards that stopped producing `reply_count` or `view_count` (page structure changed).
- Boards where pseudonym uniqueness count dropped >50% week-over-week (could be a lurker vs. regulars shift — or a scraper issue).

Any red flags go into SESSION_LOG for follow-up.

---

## Escalation rules

- **Board goes dark (403/500 for 3 sweeps)**: mark `source_registry.is_active=0`, file scrape_health `status=error` with a note, skip from weekly total.
- **Board changes ToS to disallow scraping**: even for pseudonymous public threads, pause immediately. Re-read the ToS. Escalate to Kevin before resuming.
- **Board starts showing dynamic content only**: document in the playbook update the JS trigger needed, keep running manual Cowork sweeps, don't hack around it programmatically.

---

## Provenance reminder (STRATEGY §1.2)

Every single row written by this playbook has `capture_url` populated with the exact thread URL. That URL is what the UI shows as citation. If a thread is deleted upstream, the citation breaks honestly rather than silently — do NOT substitute an archive.org link for the citation.
