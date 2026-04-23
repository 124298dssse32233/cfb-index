# Thursday Game-Week Pulse + Sunday Recap Sweep

Two playbooks share an extraction schema because they're the same motion aimed at
different moments in the game-week arc (STRATEGY §7 in-season rhythm).

- **Thursday 3:00 PM ET, 20 min** — *Game-Week Pulse*: ticket snapshot,
  line movement review, board flare-ups (72 hours before kickoff).
- **Sunday 10:00 AM ET, 30 min** — *Post-Game Recap*: emotional pulse
  across platforms ~14 hours after the final whistle.

Output of both: rows into `conversation_documents` tagged with
`source_subchannel=game_week_pulse` or `post_game_recap`, plus one
`game_pulse_snapshot` row per game observed (fields below).

---

## Shared extraction schema

Every note captured by either playbook uses this shape:

```yaml
source_id:            varies by citation (board_*, reddit_team, bluesky_firehose, radio_*, …)
source_tier:          B or D per citation
platform:             varies
game_id:              references games.game_id from the current week
game_label:           "Alabama @ Georgia — 2026 Week 13"
window_label:         "thursday_pulse" | "post_game_recap"
observed_at_utc:      ISO-8601
source_document_id:   "manual:{window_label}:{game_id}:{sequence}"
body_text:            the notable quote or observation (≤400 chars)
author_identity_class: pseudonymous | official | verified_media
capture_url:          link to the originating post / article / radio clip
canonical_url:        same
demographic_slice:    hardcore_board | reddit | media_adjacent | campus_student | radio_caller
retention_policy:     aggregated_only
ingestion_adapter_version: 0.1.0-manual
dedup_key:            sha1("{capture_url}|{observed_at_utc_hour}")
```

---

## Thursday Pulse — navigation

For every game featuring at least one **priority team** or a ranked opponent:

1. **SeatGeek snapshot** (`source_id=seatgeek`). Record:
   - Cheapest-listing price at T-72h vs. T-0.
   - Total listing count delta vs. 24h prior.
   - Any abnormal pump/dump pattern (→ `notes`).
2. **Line movement scan** (`source_id=cfbd` — data already in DB, no Cowork needed).
   - Which direction the spread moved in the last 24h, across all providers.
3. **Board flare-ups** — open each priority-team's primary message board. Any thread
   in the last 48h with >100 replies AND mentioning game-relevant keywords
   (coach name, opposing QB name, injury, officiating). Record ONE row per flare-up
   with `window_label=thursday_pulse`.
4. **Bluesky beat-writer pulse** — 3 posts per beat-writer handle from last 24h; each
   becomes a row.

**Stop at 12 rows total for the Pulse window.** Quality over quantity.

---

## Sunday Recap — navigation

Same sources, different vibe. Aim for emotional signal, not ticket arithmetic.

1. **Reddit game thread** — for each priority-team game, open the r/CFB game thread and the
   team-specific subreddit post-game thread. Top 10 highest-upvoted comments; record ONE
   row per comment worth quoting (anger, elation, tactical argument).
2. **Message-board post-mortem threads** — same top-10 rule.
3. **Local sports radio podcast episodes** — if the Monday morning radio show
   has dropped an episode before 10 AM ET, list the episode metadata. ASR is
   NOT run by default; flag any episode you want transcribed with `needs_asr=true`
   and the Whisper.cpp pipeline (TASK 7.2) picks it up.
4. **Substack quick-takes** — any priority-team Substack writer who has
   posted since Saturday evening.

**Aim 20-30 rows for the Recap window.**

---

## Per-game snapshot row

Both playbooks also produce ONE row per observed game into a helper table
`game_pulse_snapshot` (to be created in a follow-up migration once Kevin blesses):

```yaml
game_id:              integer
window_label:         "thursday_pulse" | "post_game_recap"
observed_at_utc:      ISO-8601
seatgeek_getin_cents: integer (Thursday only)
seatgeek_listings:    integer (Thursday only)
line_delta_points:    real (Thursday only)
line_direction:       "toward_home" | "toward_away" | "flat" (Thursday only)
emotional_valence:    -1..1 (Sunday, impressionistic)
top_storyline:        short string (both)
notes:                free text
capture_url:          one representative URL
```

If we don't build the helper table this week, Claude records the snapshot
row as a single `conversation_document` with `content_type=game_pulse_snapshot`
and body_text=JSON of the above — fully round-trippable for the eventual
migration.

---

## Row writing

```
python manage.py cowork-ingest-game-pulse --window=thursday_pulse --week=YYYY-WW --yaml=<paste>
python manage.py cowork-ingest-game-pulse --window=post_game_recap --week=YYYY-WW --yaml=<paste>
```

The CLI (TASK 6.5 follow-up) validates the schema and writes rows into
`conversation_documents` tagged with the window_label. Downstream, the cohort
aggregator treats Thursday and Sunday windows identically — they're both
inputs to that week's `team_cohort_week`.

---

## What NOT to capture

- **Locker-room or coach's-room audio leaked to radio** — pass.
- **Injury speculation without a team-official source** — pass. We don't
  publish medical rumors.
- **Fan-to-fan harassment** — pass. Not signal, and we don't want to amplify it.
- **Players' personal social accounts** — subject, not sample.

---

## Escalation

- **Game is delayed/suspended**: push the Recap run by 24h; the Thursday
  Pulse still stands but note `game_weather: delayed` in notes.
- **Network-wide outage of a source**: log a row to `scrape_health` with
  `status=empty`. One empty window is not a problem; three in a row is.
