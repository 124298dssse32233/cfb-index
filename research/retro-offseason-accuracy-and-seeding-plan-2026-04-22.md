# Retroactive Offseason — Accuracy And Seeding Plan

Research date: 2026-04-22
Companion to: `research/retro-offseason-content-plan-2026-04-22.md`

## Why this memo exists

The first memo answered *what we publish*. This memo answers the follow-up the user raised: **how do we make sure the numbers that drive the charts are actually accurate?** Issue N° 047's seeded numbers (`47,392`, `2.6×`, `94`, `-15`) are plausible-looking editorial fabrications from the Figma exemplar. If we ship ten retro issues with more numbers like that — mood scores, mood deltas, rivalry ratios, lexicon spikes — the product stops being defensible the first time a Michigan fan, a reporter, or a competitor asks *"where did −15 come from?"*

The bar for this series:

- **Every numeric claim on every retro page must be reproducible from a SQL query against the live DB.**
- **Every text claim must be traceable either to a cited event (coaching change, game result, roster move) or to an editorial seed string explicitly tagged as editorial.**

Nothing else. This memo makes that possible.

## The one discipline: computed vs. curated vs. hybrid

Every stat on the site falls into exactly one of these three buckets, stored as a column on every hub/mood/rivalry/lexicon row:

- `source = 'computed'` — derived end-to-end from our DB by a deterministic function. Re-running the pipeline with the same inputs must produce the same number.
- `source = 'curated'` — a human-entered fact from a cited source (e.g. "Moore fired Mar 23", "USC class #1 per 247", "Indiana 27 Miami 21"). Provenance column names the source URL.
- `source = 'editorial'` — a publication-voice string (pull quotes, cover deks, lexicon narratives) not backed by math.

**Charts may only consume `computed` and `curated`.** Editorial strings are allowed in captions and body copy but may not drive a chart axis, a leaderboard rank, or a scorecard number.

## Data we can actually get (honest read of each source)

### Reddit — this is the whole sentiment backbone

The live collector (`src/cfb_rankings/ingest/conversation.py`) uses Reddit's public JSON search and listing endpoints. Two limitations break a naive retro backfill:

1. `/r/{sub}/search.json` + `sort=new` caps at ~1000 results and does not accept a true date range — only `t={hour|day|week|month|year|all}`. Posts older than about a week on a high-traffic sub drop out of the effective search window.
2. `/r/{sub}/new.json` caps at 1000 posts total. For `r/CFB` (50–150 submissions/day), that's ~8–20 days of depth. Useless for reaching Jan 19.

Both are solvable, but only with an adapter layer on top of the existing collector:

**Primary backfill path: Pullpush.io (`https://api.pullpush.io/reddit/`)** — community Pushshift successor. Accepts `before` and `after` epoch filters plus `subreddit`, `q`, `size`, `sort`. It holds the actual historical archive. Rate limit is ~1 req/sec anonymous; bursts tolerated. This is the path we must build against; the official Reddit search endpoint will not cover Jan–Feb from an April run.

**Secondary hydration pass: official Reddit API** — once Pullpush has returned a list of post/comment IDs for a window, pull each via `/api/info.json?id=t3_xxx` (submissions) or `/api/info.json?id=t1_xxx` (comments) to get current `score`, `num_comments`, and moderation/deletion status. Pullpush's cached scores are stale; refresh them.

**Tertiary for volume-ceiling subs: `/top.json?t=month` iteration** — for each month Jan–Apr, pull top 1000 from each target sub. Useful as a hype-anchored sample even if Pullpush is degraded for that slice.

We build a thin adapter — `src/cfb_rankings/ingest/reddit_pullpush.py` — that implements the existing collector's contract (`collect_reddit_watchlist` / `collect_reddit_subreddit_listing` interfaces) but reads from Pullpush when `--date-range` is passed. No change to the ingest feature-builder downstream.

### CFBD Tier 2 — authoritative for football structure

Trusted for: final bracket, championship box score, season-end team records, `team_talent_snapshots`, `recruiting_entries`, `returning_production`, schedule. No fictionalization needed — `ingest-cfbd-week --season 2025 --week 21 --season-type postseason` captures the Indiana win cleanly.

### Portal / carousel / NFL declarations — curated ledger only

Tier 3 transfers aren't in our subscription. We manually curate three JSON files under `data/offseason/2026/`:

- `coaching_changes.json` — one row per P4 HC change + notable G5 moves. ~40 rows. Fields: program, change_type (fire|hire|resign|promote), announce_date, outgoing, incoming, grade_a_plus_to_d, source_url.
- `portal_moves.json` — top 75 portal moves by composite rating. ~75 rows. Fields: player_name, from_team_slug, to_team_slug, position, composite_stars, announce_date, source_url, notes.
- `nfl_declarations.json` — top 40 early-entry declarations + Arch Manning stay + notable undeclareds. ~40 rows. Fields: player_name, team_slug, decision (declare|return|medical), announce_date, projected_round, source_url.

These are small, bounded, and every row is traceable. Pattern precedent: Issue 047's seed dicts in `hub_data.py`.

### Spring calendar — curated with Tier 2 team IDs

`spring_events.json` — ~30 rows. Fields: team_slug, event_type (practice_open|presser|spring_game|qb_battle_resolved|qb_injury), event_date, headline, qb1_read, source_url. Joined at ingest time to `teams.team_id`.

### What we will *not* make up

- We will not invent mood indices. Every `mood_score` cell is either `source='computed'` with a backing SQL query, or absent (NULL, with `source=NULL`).
- We will not invent obsession ratios. Every `ratio_dominant` cell is computed from actual comment cross-mentions, or the row doesn't ship.
- We will not invent lexicon spike percentages. Every `spike_pct_wow` cell is computed from actual n-gram frequency counts.
- We will not invent a "47,392 times" number unless that number is actually the count query result.

The retro Issue 047 pass should rewrite its three cards against the computed pipeline. If the computed numbers disagree with the current editorial seed, we update the editorial seed — not the other way around.

## The alias + token dictionary (cheap first-pass filter)

Every piece of Reddit text we ingest gets tagged by regex before any LLM touches it. Four dictionaries, all seed-extendable:

### Team aliases

Already present via `team_aliases_for_season()` (post-fix per `offseason-publishing-queue-and-build-order`). For retro we extend with:

- **Coach aliases** per program: `"Sherrone Moore"|"Moore"|"SMoore"|"@CoachSMoore"` → michigan. Coach aliases *override* plain-name matches: a post mentioning "Moore" in an r/CFB thread about Michigan firing is a Michigan-coach hit, not a false positive from some other Moore.
- **QB1 aliases**: `"Mendoza"`, `"Raiola"`, `"Mensah"`, `"Leavitt"`, `"Manning"|"Arch"`, `"Carr"` — per team, time-bounded (Raiola is NEB→ORE on Jan 8).
- **Nickname aliases**: `"skunkbears"` → michigan; `"TTUN"` → michigan; `"Sakerlina"` → south-carolina; etc. Already partly present.

### Sentiment lexicon

Three ordered buckets, regex-matched, de-negated (`"not cooked"` is not a `cooked` hit):

```
POSITIVE: back, him, cook, cooking, trust, locked in, stock up, this is it,
          roll, we're fine, clean, elite, real, generational, HIM, HIM behavior

NEGATIVE: cope, cooked, dead, fired, doomed, mid, trash, no shot, fraud,
          stock down, nfl'd out, over, it's over, transfer out, wasted year,
          panic

INTENSIFIER: !, !!!, CAPS-LOCK word, 🔥 3x+, ❌, literal emoji counts 1.5x
```

A doc's sentiment polarity = `(count(POSITIVE) - count(NEGATIVE)) * (1 + 0.3 * count(INTENSIFIER))`, normalized to [-1, 1]. This is the cheap first-pass; low-confidence docs get routed to a Haiku classification call only if they're in the top-volume slices that drive a public number.

### Event tokens

Trigger the Shock Index anchor logic. Per event family:

```
CAROUSEL: /\b(fired|hired|signs with|named HC|steps down|mutual parting|out at)\b/
PORTAL:   /\b(enters (the )?portal|commits to|flips to|decommits|hits portal)\b/
DRAFT:    /\b(declares for (the )?nfl( draft)?|returning for senior year|last dance)\b/
NIL:      /\b(bag|NIL|collective|\$\d+[MK]\s*(nil)?)\b/
INJURY:   /\b(torn|acl|out for (spring|fall)|season-ending)\b/
```

A doc matching an event token + a team alias stamps the `conversation_documents` row with `event_type` so the Shock Index can group and weight.

### Rivalry-pair tokens

For each of the 12 canonical rivalries in `RIVALRY_SEED_047`, a regex that matches "Team A vs Team B"-shaped references in a doc from one side's sub:

- `r/OhioStateFootball` post mentioning `/\b(mich(igan)?|UM|ttun|skunkbears|harbaugh|moore|whittingham)\b/i` → counts as `ohio-state → michigan` rivalry mention.
- `r/MichiganWolverines` post mentioning `/\b(osu|ohio\s*state|scarlet and gray|day(ian)?|sayin)\b/i` → `michigan → ohio-state` rivalry mention.

Each side maintains its own regex so "Michigan" inside an r/CFB thread doesn't get double-counted as a rivalry mention by either sub.

## Formulas — every number we show, explicit

**Notation.** For team `t`, week `w`, bucket `b ∈ {fan, national, rival}`:
- `D(t,w,b)` = set of `conversation_documents` rows matching team `t` in bucket `b`, `posted_at` within `[w_start, w_end)`.
- `P(t,w,b)` / `N(t,w,b)` / `U(t,w,b)` = positive / negative / neutral doc counts by the sentiment lexicon.
- `V(t,w,b) = |D(t,w,b)|` = volume.
- `B(t,w)` = baseline volume, the trimmed mean `V(t, w-4..w-1, b)` — the "normal" 4-week volume.

### Mood Index `M(t, w)` ∈ [0, 100]

```
raw = (P - N) / max(P + N, MIN_MENTIONS_FOR_SIGNAL)          # [-1, 1]
conf = min(1, (P + N) / 50)                                  # confidence ramp
M = round(50 + 40 * conf * raw)                              # [10, 90]
clamp to [0, 100]
```

- `MIN_MENTIONS_FOR_SIGNAL = 12` (matches the existing gate).
- Below the gate: `M = NULL, source = NULL`. The team renders "Awaiting Signal."
- Bucket selection: default `fan` if the team sub has ≥ MIN samples, else fall back to `national` — and record which bucket was used in `M_bucket`. Never silently blend.
- Published value is clamped to [10, 90] except for extreme-event weeks (championship Monday, firing Monday) where the clamp widens to [5, 95].

Chart use: Mood River (line across weeks), Small Multiples (sparklines), point annotations.

### Mood Delta `ΔM(t, w)`

```
ΔM = M(t, w) - M(t, w-1)
```

- If either week is below the gate, `ΔM = NULL`.
- `ΔM` is what Issue 047's MOOD_SEED column labeled "delta". The retro pipeline replaces each of those 10 hand-picked deltas with the computed value; the editorial "cause" phrase stays curated (e.g. "Moore presser").

### Reality Gap `RG(t, w)` ∈ {Hype Train, A Little Ahead, Grounded, A Little Too Low, Doomer Ball}

```
belief_pct = percentile_rank(M(t, w), M(·, w)) over all FBS teams this week
power_pct  = percentile_rank(power_rating(t, w), power_rating(·, w))
gap = belief_pct - power_pct                                  # in [-100, 100]

gap > 25             → Hype Train
10 < gap ≤ 25        → A Little Ahead
-10 ≤ gap ≤ 10       → Grounded
-25 ≤ gap < -10      → A Little Too Low
gap < -25            → Doomer Ball
```

Chart use: quadrant plot (belief_pct x power_pct), dumbbell rail.

### Respect Gap `RSP(t, w)`

```
self_M     = M(t, w, fan)          # from team sub
outside_M  = M(t, w, national)     # from r/CFB posts mentioning team
RSP = self_M - outside_M           # [-100, 100], positive = underrated externally
```

- Requires both buckets above gate. Below gate on either side → NULL.
- Chart use: dumbbell — team abbr on x-axis, two dots (self_M, outside_M), line between.

### Swing `SW(t, w)` ∈ {Full Roller Coaster, Swingy, Reactive, Steady}

```
σ = stddev(M(t, w-8..w))           # 8-week rolling std
σ > 10      → Full Roller Coaster
6 < σ ≤ 10  → Swingy
3 < σ ≤ 6   → Reactive
σ ≤ 3       → Steady
```

For retro weeks 22–30 the 8-week rolling window is incomplete until Week 26. Before that we publish σ over available weeks with a `SW_confidence` flag.

### Cohesion `C(t, w)` ∈ {Civil War, Split, Tense, United}

Computed on the **coach-attitude** axis (the clearest fanbase-split axis), not on general sentiment. Two additional regex groups:

```
PRO_COACH:  /\b(in\s+\w+\s+we\s+trust|trust\s+\w+|\w+\s+is\s+the\s+guy|extend\s+\w+)\b/
ANTI_COACH: /\b(fire\s+\w+|\w+\s+must\s+go|\w+\s+gotta\s+go|done\s+with\s+\w+)\b/
```

(The `\w+` should resolve to that team's current HC alias — the regex is dynamic per team-week.)

```
pro, anti = counts in team sub over the week
split = min(pro, anti) / max(pro, anti)       # [0, 1]
split > 0.8   → Civil War
0.5 < split ≤ 0.8  → Split
0.3 < split ≤ 0.5  → Tense
split ≤ 0.3   → United
```

- Requires `pro + anti ≥ 20` or `C = NULL`.
- Chart use: Fanbase Civil War Watch homepage rail.

### Rival Heat `RH(t, w)` ∈ {Rent Free, High, Moderate, Low}

```
rival_mentions = count of docs in D(t, w, fan) that match the team's primary rival regex
self_mentions  = V(t, w, fan)
ratio = rival_mentions / max(self_mentions, 1)

ratio > 0.5       → Rent Free
0.3 < ratio ≤ 0.5 → High
0.15 < ratio ≤ 0.3 → Moderate
ratio ≤ 0.15      → Low
```

- Computed only if `self_mentions ≥ 50`.
- Chart use: Rival Heat Matrix (12 canonical rivalries × heat level color).

### Rivalry Obsession Ratio — populates `rivalry_obsession_weekly`

Issue 047 seed currently claims "Michigan fans mention Ohio State 2.6× as often as Ohio State fans mention Michigan." The computed version:

```
a_to_b_rate = (rival_mentions from r/{A_sub} of B) / V(A, w, fan)
b_to_a_rate = (rival_mentions from r/{B_sub} of A) / V(B, w, fan)

ratio_dominant = max(a_to_b_rate, b_to_a_rate) / min(a_to_b_rate, b_to_a_rate)
leaning_team = 1 if a_to_b_rate > b_to_a_rate else 2 (or 0 if within 5%)
```

- Normalizing by `V` prevents the result from being driven by sub size. r/MichiganWolverines has ~120k subs, r/OhioStateFootball has ~150k. Raw counts over-represent whichever sub is larger; rates cancel that out.
- Requires `V(A) ≥ 100` and `V(B) ≥ 100` in the fan bucket, or no ratio ships.
- Chart use: Rivalry Matrix rows, leaning arrows.

### Shock Index `S(t, w)` (event-anchored mood delta)

The Shock Index is the one metric that bridges curated events and computed sentiment:

```
# For each event e in coaching_changes ∪ portal_moves ∪ nfl_declarations ∪ spring_events
# where e.announce_date ∈ [w_start, w_end) and e.team_id = t:

pre_window  = docs in D(t, [e.announce_date - 3d, e.announce_date))
post_window = docs in D(t, [e.announce_date, e.announce_date + 3d))

pre_raw  = (P(pre) - N(pre)) / max(P(pre) + N(pre), MIN)
post_raw = (P(post) - N(post)) / max(P(post) + N(post), MIN)
event_delta = 40 * (post_raw - pre_raw)          # in mood-index points

volume_spike = V(post) / max(V(pre), 1)           # multiplier
S_event = round(event_delta * min(log2(volume_spike + 1), 3))   # caps at 3x
```

- Capped so one event can never single-handedly move more than ~30 mood points.
- The retro Issue's "Shock Index v1" shows a ranked table of all events in that week's bucket with `S_event` and a one-line computed caption ("Raiola exit, r/Huskers, −10 pts, 2.4× volume").

### Lexicon Spike `spike_pct_wow`

For each tracked phrase `p`:

```
this_week_count = count of docs matching p regex in the target sub, within this week
prior_avg       = trimmed mean of phrase count in that sub over previous 4 weeks
spike_pct_wow   = 100 * (this_week_count / max(prior_avg, 5)) - 100
```

- Publish gate: `this_week_count ≥ 50 AND spike_pct_wow ≥ 100`. Below that, phrase appears in the lexicon archive rail, not the featured slot.
- Discovery: a secondary pass computes weekly n-gram (2..4) frequency across target subs and surfaces novel phrases whose `spike_pct_wow > 200` for editorial review. This is how we find the next "5-star trust me" instead of hardcoding it.

### Volume `V(t, w)` — sample size badge

Raw doc count in each team-week-bucket. Published as the "sample" number on the Mood Card ("340,000" in Issue 047 is a hand-wave; the real number will be the actual `V`). Displayed with a confidence bar: low (< 50), medium (50–200), high (> 200).

## What each retro issue actually needs (seed-vs-compute map)

Each of the ten retro issues has an explicit table of what is computed, curated, and editorial. Rendered below as a compact matrix.

### Issue N° 038 — Perfect Hoosiers (Week 22, Mon Jan 19)

| Element | source | provenance |
|---|---|---|
| Cover headline "Perfect Hoosiers" | editorial | — |
| Indiana 27, Miami 21 | curated | NCAA.com, CFP site |
| Indiana 16–0 | curated | Same |
| Mendoza line (16/27, 186, rushing TD, MVP) | curated | CFP recap |
| Mood Index snapshot (10 teams) | computed | Pullpush Jan 12–19 backfill |
| Mood delta WoW | computed | Vs. Week 21 |
| Mood River chart (Indiana arc across season) | computed | 16 weekly points from live DB + Week 22 |
| Commiseration body (Miami) | editorial | — |
| Lexicon "the pick on the 44" count | computed | n-gram search r/CFB + r/IUFootball |
| Lexicon narrative | editorial | — |
| Sample size badge per card | computed | V() |

### Issue N° 039 — Portal Wave Peaks (Week 23, Mon Jan 26)

| Element | source | provenance |
|---|---|---|
| Raiola → Oregon cover | curated | PFF tracker, CBS tracker |
| Shock Index table (Neb, LSU, Miami, ND) | computed | portal_moves join + 6-day mood windows |
| Mood deltas | computed | — |
| Respect Gap Census rows | computed | RSP(·, 23) for all FBS teams above gate |
| Oregon-Washington ratio shift | computed | rivalry_obsession_weekly(week=23) |
| Editor note | editorial | — |

### Issue N° 040 — Carousel Aftershock (Week 24, Mon Feb 2)

| Element | source | provenance |
|---|---|---|
| Whittingham-to-Michigan hire fact | curated | CBS carousel tracker |
| Coaching Carousel Ledger (33 rows) | curated | coaching_changes.json |
| Michigan mood +3 bump | computed | ΔM(michigan, 24) |
| Cohesion split (Michigan, LSU) | computed | C(·, 24) with PRO/ANTI_COACH regex |
| Living Rent Free (national-bucket only) | computed | Coach-name mention ratios |
| Lexicon ("Whitt happens", "Lane Train") | computed | n-gram pass |
| Cover dek | editorial | — |

### Issue N° 041 — Signing Day Truths (Week 25, Mon Feb 9)

| Element | source | provenance |
|---|---|---|
| Top-10 class table (USC #1, etc.) | curated | 247, ESPN, CBS NSD recaps |
| Composite stars per program | curated (CFBD T2) | `recruiting_entries` |
| Class delta vs predecessor | computed | team_talent_snapshots comparison |
| Hope Inventory rows | computed | r/{team} token density |
| Respect Gap on classes | computed | Class-composite percentile vs fan-belief percentile |
| Lexicon ("5-star trust me") | computed | First confirmed spike week |
| USC historical framing (first non-SEC since '08) | curated | CBS article quote + internal history |

### Issue N° 042 — Spring Opens (Week 26, Mon Feb 23)

| Element | source | provenance |
|---|---|---|
| Practice-open dates | curated | spring_events.json (On3) |
| Arch Manning limited note | curated | Sarkisian quote, On3 |
| QB Panic Meter list | computed | Compound: ΔM AND rival-at-QB presence AND coach-anxiety tokens |
| Returning Production Dashboard | curated (CFBD T2) | `returning_production` table |
| Mood Board refresh | computed | M(·, 26) |

### Issue N° 043 — Hype Train Check (Week 27, Mon Mar 2)

| Element | source | provenance |
|---|---|---|
| Reality Gap Board (all FBS) | computed | RG(t, 27) for every team above gate |
| Quadrant plot (belief vs power) | computed | belief_pct vs power_pct scatter |
| Storyline Gravity top-12 | computed | `conversation_storylines` volume rank |
| Lexicon ("cope", "doomposting") | computed | n-gram pass |

### Issue N° 044 — The Moore Presser (Week 28, Mon Mar 9)

| Element | source | provenance |
|---|---|---|
| Moore presser fact | curated | spring_events.json (date + quote line) |
| Michigan mood −15 | computed | ΔM(michigan, 28) — **this must match** the Issue 047 cover claim or one of them is wrong |
| Shock Index (Michigan, Alabama, USC) | computed | — |
| Cohesion — Michigan Civil War | computed | C(michigan, 28) |
| Camp Panic Meter | computed | Compound metric (defined in next section) |
| Lexicon ("hold the line", "in Day we trust") | computed | First confirmed spike week |

### Issue N° 045 — Michigan Moves On (Week 29, Mon Mar 23)

| Element | source | provenance |
|---|---|---|
| Moore fired / Whittingham hired | curated | coaching_changes.json |
| Exact announce date | curated | Primary reporting |
| Shock Index (Michigan +X) | computed | S_event anchored to announce_date |
| Living Rent Free (Ohio State → Michigan) | computed | Cross-sub mention flow |
| Swing Meter — Michigan Full Roller Coaster | computed | σ(M(michigan, 22..29)) |
| Nebraska spring game mood follow-through | computed | ΔM(nebraska, 29) |

### Issue N° 046 — Spring Games And Stock (Week 30, Mon Apr 6)

| Element | source | provenance |
|---|---|---|
| Spring-game ledger | curated | spring_events.json |
| Michigan QB problem post-spring | hybrid | computed ΔM + editorial framing |
| Shock Index final retro table | computed | — |
| Hope Inventory post-spring | computed | — |
| Preseason Truth Detector v1 | computed | Power rank vs consensus poll delta |

### Issue N° 047 — already published (Week 31, Apr 22)

After the retro backfill runs, rewrite all three of the existing N° 047 cards against computed numbers. The "47,392 times Nebraska said 'we're back'" number is replaced with the actual Reddit count; the "2.6×" Michigan-OSU ratio with the actual computed ratio; the "94 Georgia mood index" with the actual computed M.

If the computed numbers disagree materially with the current seed (e.g. computed Michigan-OSU ratio comes out 1.8×, not 2.6×), the editorial copy gets revised to match. Not the other way around.

## Compound metrics (defined once, cited by issues)

### QB Panic Meter

Per team in a given week:

```
panic_score = 0
if team has active QB battle per spring_events.qb_battle_resolved=false → +2
if M(team, w, fan) < 50 AND ΔM(team, w) ≤ -5 → +2
if ANTI_COACH tokens > 20 in week → +1
if a rival QB just committed to a peer program this month → +1
```

Rank top 10 by `panic_score`. Ties broken by |ΔM|.

### Camp Panic Meter

Similar shape, but opens at spring-practice-start and pulls from a wider regex (`/\b(depth chart|starter|nobody\s+knows|still\s+figuring|position\s+battle)\b/`).

### Hope Inventory

```
For each team t:
  hope_tokens = count in r/{t} of /\b(this year|finally|we're back|year 2|next level|light at end)\b/
  hope_rate = hope_tokens / V(t, w, fan)
```

Rank descending by `hope_rate`. Publish only rows with `V(t, w, fan) ≥ 100`.

### Living Rent Free

For each ordered pair `(A, B)`:

```
mentions_of_B_on_A = docs in r/{A_sub} this week containing B's rival regex
rate = mentions_of_B_on_A / V(A, w, fan)
```

Rank top 10 `(A, B)` pairs by `rate`. Interesting because it should show asymmetric pairs (Michigan → Ohio State high, Ohio State → Michigan lower) that justify the "little brother" editorial line.

## Calibration — how we know the numbers are real before we publish

Before any retro issue ships, the backfill must pass these **directional sanity checks**. They are objective, cheap, and if any fail, something's wrong with the collector or the formula, not with reality.

| Check | Expected | Fails if |
|---|---|---|
| M(indiana, 22, fan) | ≥ 85 | championship week no spike |
| M(miami, 22, fan) | ≤ 40 | loss doesn't register |
| V(indiana, 22, fan) / V(indiana, 21, fan) | ≥ 3× | volume doesn't spike on title |
| ΔM(nebraska, 23) | ≤ −8 | Raiola exit doesn't hurt |
| ΔM(oregon, 23) | ≥ +3 | Raiola arrival doesn't help |
| ΔM(usc, 25) | ≥ +5 | #1 class doesn't lift USC |
| ΔM(michigan, 28) | ≤ −10 | Moore presser doesn't collapse |
| C(michigan, 28) | Civil War or Split | Michigan fans unified? no |
| Top phrase in r/OhioStateFootball, Week 30 | "5-star trust me" or a close variant | discovery pass broken |
| Rivalry ratio michigan↔ohio-state, Week 22 post-natty | > 1.5, Michigan-leaning | regex broken |

All ten checks run as a `python manage.py retro-calibrate --season 2025` subcommand. Output is a pass/fail table with the computed numbers. No retro issue publishes until the checks for its week pass.

## Failure-mode policy — what happens when the data is thin

Some weeks / teams will fall below the gate even after Pullpush backfill. r/MissouriTigers has ~8k subscribers and posts maybe 15–20 items/day; its fan-bucket M for most weeks will be NULL.

Policy:

1. **A NULL row does not stop the issue.** The issue ships with the team omitted from that week's Mood Board, not with a fake number. The editorial cover copy must not reference that team's number if it's NULL.
2. **Board rows require at least 8 teams above gate.** If fewer than 8 qualify, the board is replaced by a "Thin Signal Week" panel with the qualifying teams listed and an editorial note.
3. **No issue is suppressed.** Every week 22..30 gets a page. When the numbers are too thin for the full Hub treatment, the issue renders a shorter "Field Notes" layout: cover + 3 cards + an editorial note, no board.
4. **Provenance badge on every card.** Mood Card, Shock Index entry, Lexicon entry — each shows a small badge: `computed`, `curated`, or `editorial`. Users see what's math and what's voice.

## Operational plan

### One-time backfill cost (hours, money, disk)

- Pullpush collection: 10 weeks × 30 teams × 3 buckets = 900 slices × ~3 sec/slice = **~45 min wall time** at 1 req/sec with some retry overhead.
- Reddit hydration pass for top 50k docs: 50k / 100 per batch = 500 req × 1 sec = **~8 min**.
- Disk: ~1M docs × ~2 KB = **~2 GB** added to `cfb_rankings.db`.
- LLM cost (Haiku only for low-confidence docs, ~5% of corpus): ~50k docs × 150 tokens × $0.25 / M = **~$2**.
- Human-curated ledger work: ~6 hours to write `coaching_changes.json`, `portal_moves.json`, `nfl_declarations.json`, `spring_events.json` against cited sources.

Total: ~8 human-hours + ~1 hour of machine time + ~$2 in LLM. Trivial.

### Suggested CLI additions

```
python manage.py seed-offseason-weeks --season 2025
python manage.py seed-offseason-events --season 2025 --kind carousel
python manage.py seed-offseason-events --season 2025 --kind portal
python manage.py seed-offseason-events --season 2025 --kind nfl
python manage.py seed-offseason-events --season 2025 --kind spring

# Pullpush-backed backfill (per week):
python manage.py backfill-offseason-conversation \
  --season 2025 --week 22 --from 2026-01-19 --to 2026-01-26 \
  --subs "r/CFB,r/IUFootball,r/MiamiHurricanes,r/MichiganWolverines,...,r/Huskers" \
  --source-adapter pullpush

# Feature builder (existing) — runs per week after backfill:
python manage.py build-conversation-features --season 2025 --week 22

# New: retro calibration gate
python manage.py retro-calibrate --season 2025 --weeks 22..30

# New: retro hub seed (editorial-only fallback copy + provenance tags)
python manage.py seed-hub-issue-retro --season 2025 --week 22
... (through week 30)

# Finally, build the site:
python manage.py build-site
```

### Weekly run order (repeatable)

1. `seed-offseason-weeks` (once)
2. `seed-offseason-events --kind ...` (once per kind)
3. For `w in 22..30`:
   1. `backfill-offseason-conversation --week w --from DATE --to DATE --subs ...`
   2. `build-conversation-features --week w`
   3. `seed-hub-issue-retro --week w`
4. `retro-calibrate --weeks 22..30` → **must pass**
5. `build-site`

### Observability hooks

Every retro-pipeline command writes a run summary JSON to `logs/retro/<date>/<command>.json`:

```
{
  "command": "backfill-offseason-conversation",
  "season": 2025,
  "week": 22,
  "subs": [...],
  "docs_fetched": 14823,
  "docs_inserted": 14780,
  "docs_duplicate": 43,
  "teams_above_gate": 62,
  "teams_below_gate": 6,
  "duration_seconds": 241.2,
  "pullpush_errors": 2,
  "hydration_hits": 14780
}
```

This is the audit trail. Any retro-issue page can link its "show your work" footer to the JSON that produced its numbers.

## Revised schema implications (minor)

Added to the four new tables in the primary memo:

- **`fanbase_mood_weekly.source` TEXT** — `'computed' | 'curated' | 'editorial'`.
- **`fanbase_mood_weekly.sample_size` INT** — now the real `V`, not a hand-wave.
- **`fanbase_mood_weekly.bucket_used` TEXT** — `'fan' | 'national'` so the page can show which audience produced the number.
- **`fanbase_mood_weekly.confidence` REAL** — the `conf` term from the formula, for rendering confidence bars.
- **`rivalry_obsession_weekly.source` TEXT** — same three-value tag.
- **`lexicon_weekly.source` TEXT** — same.
- **`hub_issue_metadata.cards_json[i].source` per card** — same.
- **`conversation_storylines.event_refs` JSON** — optional list of `(table, id)` pointers into `coaching_changes` / `portal_moves` / `nfl_declarations` / `spring_events` so storylines can be joined back to the underlying curated events.

These are three-char column additions; the migration stays tiny.

## What this buys us

- **A Michigan fan** can click any number on any retro issue and see a badge telling them whether it's math or editorial. They'll argue with the formula, not with our honesty.
- **A reporter** can reproduce any stat by running the same SQL. No black box.
- **Future seasons** inherit the same pipeline. The formulas above are the site's permanent metric spec — Issue 047 becomes the first issue where those formulas run against live data instead of seeded data.
- **Editorial** stays in the driver's seat on voice and narrative framing, but no longer invents numbers. Which means the voice gets to be bolder, because the numbers have stopped being the thing the voice has to defend.

## Open questions for Kevin

1. **Pullpush.io terms.** The community Pushshift mirror has been intermittently rate-limited and lightly terms-of-service-gray. Is using it for a one-time backfill acceptable, or should we instead negotiate access to a proper historical Reddit archive (Anthropic-internal, Bright Data, etc.)? This affects the P0 timeline — official Reddit API alone cannot reach Jan 2026 from April.
2. **Haiku vs Sonnet for sentiment fallback.** 5% of the corpus (~50k docs) needs classification beyond regex. Haiku is fine for polarity; the question is whether we want the storyline-ranking step to use Sonnet for better narrative coherence. Budget impact: ~$2 (Haiku) vs ~$20 (Sonnet). Recommend Haiku for the bulk and Sonnet only for the top 500 storyline candidates per week.
3. **Lexicon discovery threshold.** `spike_pct_wow > 200` feels right as a discovery trigger. Want to confirm before I bake it into the `mine-lexicon` subcommand. Too loose and we flood the editorial review queue; too tight and we miss the next "5-star trust me."
4. **Should Issue 047 be rerun?** Once the backfill completes, the existing Issue 047 cover numbers will be either confirmed or contradicted by computed equivalents. Default plan is to rewrite Issue 047's cards to match the computed numbers — but if the editorial seed is load-bearing for the Figma exemplar / external demo, we could alternatively publish a second issue ("N° 047.1 — The Audited Edition") that shows the computed numbers with the editorial cards annotated. I'd recommend the first option (overwrite) for product integrity, but it's your call.

## Sources (for this memo, beyond the primary)

- [Pullpush.io API docs](https://api.pullpush.io/)
- [Reddit API listing endpoints](https://www.reddit.com/dev/api)
- [CFBD API tiers](https://collegefootballdata.com/api-tiers)
- Primary event sources — same as `retro-offseason-content-plan-2026-04-22.md`.
